const tokenManager = require('./tokenManager')
const axios = require('axios')
const fs = require('fs').promises
const path = require('path')
/* you need to add a config.json file to your plugin
directory holding the config infor for your install similar 
to 
{
  "serverBaseUrl": "http://localhost",
  "clientId": "a UUID or other client identifier",
  "description": "description of this client"
}

*/
const config = require('./config.json')

//global variables go here
const serverBaseUrl = config.serverBaseUrl
const clientId = config.clientId
const description = config.description
let token = null
let rodeDeployed = 0
let anchorDropped = false
let depth = 0
let rodeLength = 0
let bowHeight = 0
let unsubscribes = []

module.exports = (app) => {
    const plugin = {
        id: 'signalk-anchorAlarmConnector',
        name: 'anchorAlarmConnector',
        start: async (settings, restartPlugin) => {
            token = await tokenManager.getToken(
                serverBaseUrl,
                clientId,
                description
            )
            if (!token) {
                console.error('Failed to obtain token.')
                return
            }
            console.log('Token obtained:', token)

            // Uncomment line below to run test sequence
            // runTestSequence()

            /*delaying 3 seconds so the needed paths 
            can be established at startup*/
            setTimeout(() => {
                rodeDeployed = app.getSelfPath(
                    'navigation.anchor.rodeDeployed'
                )?.value
                anchorDropped =
                    app.getSelfPath('navigation.anchor.position')?.value != null
                depth = app.getSelfPath('environment.depth.belowSurface')?.value
                rodeLength = app.getSelfPath(
                    'navigation.anchor.rodeLength'
                )?.value
                bowHeight =
                    app.getSelfPath('design.bowAnchorHeight')?.value || 0

                console.log(rodeDeployed, anchorDropped, depth, rodeLength)
            }, 3000)

            app.subscriptionmanager.subscribe(
                {
                    context: 'vessels.self',
                    subscribe: [
                        {
                            path: 'navigation.anchor.rodeDeployed',
                            period: 1000,
                        },
                        { path: 'navigation.anchor.position', period: 1000 },
                        { path: 'navigation.anchor.rodeLength', period: 1000 },
                        {
                            path: 'environment.depth.belowSurface',
                            period: 1000,
                        },
                    ],
                },
                unsubscribes,
                (err) => {
                    app.error('Subscription error:', err)
                },
                (delta) => {
                    delta.updates.forEach((update) => {
                        update.values.forEach((v) => {
                            const path = v.path
                            const value = v.value
                            if (path === 'navigation.anchor.rodeDeployed') {
                                let previousRode = rodeDeployed
                                let newRode = value
                                app.debug(
                                    'newRode',
                                    value,
                                    ' previousRode',
                                    previousRode,
                                    ' depth',
                                    depth,
                                    ' anchorDropped',
                                    anchorDropped
                                )
                                if (
                                    newRode > previousRode &&
                                    newRode > depth + bowHeight &&
                                    !anchorDropped
                                ) {
                                    sendAnchorCommand('dropAnchor')
                                }
                                if (
                                    newRode < previousRode &&
                                    anchorDropped &&
                                    newRode < depth + bowHeight
                                ) {
                                    sendAnchorCommand('raiseAnchor')
                                }
                                if (newRode != rodeLength && anchorDropped) {
                                    sendAnchorCommand('setRodeLength', {
                                        length: newRode,
                                    })
                                }
                                rodeDeployed = newRode
                            } else if (path === 'navigation.anchor.position') {
                                app.debug('Anchor position changed:', value)
                                anchorDropped = value != null
                            } else if (
                                path === 'navigation.anchor.rodeLength'
                            ) {
                                app.debug('Rode length changed:', value)
                                rodeLength = value
                            } else if (
                                path === 'environment.depth.belowSurface'
                            ) {
                                depth = value
                            }
                        })
                    })
                }
            )
        },

        stop: () => {
            unsubscribes.forEach((f) => f())
            unsubscribes = []
        },
        schema: () => {
            return {
                type: 'object',
                required: ['some_string', 'some_other_number'],
                properties: {
                    some_string: {
                        type: 'string',
                        title: 'Some string that the plugin needs',
                    },
                    some_number: {
                        type: 'number',
                        title: 'Some number that the plugin needs',
                        default: 60,
                    },
                    some_other_number: {
                        type: 'number',
                        title: 'Some other number that the plugin needs',
                        default: 5,
                    },
                },
            }
        },
    }
    async function sendChange(path, value) {
        app.handleMessage(
            'netmonitor',
            {
                updates: [
                    {
                        values: [
                            {
                                path: path,
                                value: value,
                            },
                        ],
                    },
                ],
            },
            'v1'
        )
    }
    async function sendAnchorCommand(command, params = {}) {
        if (!token) {
            console.error('No token available. Please authenticate first.')
            return
        }
        // console.log(`Sending "${command}" command with params:`, params)
        // console.log(`Using token: ${token}`)
        try {
            const response = await axios.post(
                `${serverBaseUrl}/plugins/anchoralarm/${command}`,
                params,
                {
                    headers: {
                        Authorization: 'Bearer ' + token,
                        'Content-Type': 'application/json',
                    },
                }
            )
            console.log(
                `"${command}" command sent successfully:`,
                response.data
            )
        } catch (error) {
            console.error(
                `Error sending "${command}": `,
                error.response ? error.response.data : error.message
            )
        }
    }
    /* Example usage:
            sendAnchorCommand('dropAnchor');
            sendAnchorCommand('raiseAnchor');
            sendAnchorCommand('setRodeLength', { length: 50 });
            */

    function runTestSequence() {
        console.log('Starting test sequence...')
        sendChange('environment.depth.belowSurface', 5)
        sendChange('navigation.position', {
            longitude: -79.38,
            latitude: 43.65,
        })
        console.log(rodeDeployed, anchorDropped, depth, rodeLength)
        //uncomment below to run test sequence that drops and raises anchor
        // wait 35 seconds then drop anchor
        // setTimeout(() => {
        //     sendAnchorCommand('dropAnchor')

        //     setTimeout(() => {
        //         sendChange('navigation.position', {
        //             longitude: -79.38,
        //             latitude: 43.649823,
        //         })
        //         sendAnchorCommand('setRodeLength', { length: 50 })
        //         // wait another 5 seconds then raise anchor
        //         setTimeout(() => {
        //             sendAnchorCommand('raiseAnchor')
        //         }, 35000)
        //     }, 5000)
        // }, 3000)
    }

    return plugin
}
