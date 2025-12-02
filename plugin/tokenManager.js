// tokenManager.js
const fs = require('fs').promises
const path = require('path')
const axios = require('axios')

const tokenFilePath = path.join(__dirname, 'data', 'token.json')

async function loadToken() {
    try {
        const data = await fs.readFile(tokenFilePath, 'utf8')
        const json = JSON.parse(data)

        if (json.token) {
            if (json.expiration === null) {
                console.log('Loaded token (never expires).')
                return { token: json.token, expiration: null }
            }

            const expirationTime = Number(json.expiration)
            if (isNaN(expirationTime)) {
                console.log('Expiration is invalid.')
                return null
            }

            if (Date.now() < expirationTime) {
                console.log('Loaded valid token from disk.')
                return { token: json.token, expiration: expirationTime }
            } else {
                console.log('Stored token expired.')
            }
        }
    } catch (err) {
        console.log('No stored token or error reading file.')
    }
    return null
}

async function saveToken(token, expirationTime) {
    const data = {
        token: token,
        expiration: expirationTime ? new Date(expirationTime).getTime() : null,
    }
    await fs.writeFile(tokenFilePath, JSON.stringify(data))
    console.log(
        'Token saved with expiration:',
        expirationTime || 'never expires'
    )
}

async function requestToken(serverUrl, clientId, description) {
    try {
        const response = await axios.post(
            `${serverUrl}/signalk/v1/access/requests`,
            {
                clientId,
                description,
            }
        )

        // If the response is successful, the status is 2xx, and axios doesn't throw.
        const { href } = response.data
        console.log('Access request sent. Waiting for approval...')

        const tokenData = await pollForApproval(serverUrl, href)

        if (tokenData) {
            const { token, expiration } = tokenData
            await saveToken(token, expiration)
            console.log('******APPROVED AND TOKEN SAVED******')
            return { token, expiration }
        } else {
            console.log('Access was denied or failed.')
            return null
        }
    } catch (err) {
        // Axios throws for non-2xx responses so you catch errors here
        console.error('Error during token request:', err)
        return null
    }
}

// Polling function to wait until approval
async function pollForApproval(serverUrl, requestUrl) {
    while (true) {
        await new Promise((r) => setTimeout(r, 5000))
        const statusRes = await axios.get(`${serverUrl}${requestUrl}`)
        if (statusRes.status !== 200) {
            console.error('Failed to get status:', statusRes.status)
            return null
        }
        const data = statusRes.data

        if (data.state === 'PENDING') {
            console.log('Request still pending...')
            continue
        } else if (data.state === 'COMPLETED') {
            const permission = data.accessRequest.permission
            if (permission === 'APPROVED') {
                const token = data.accessRequest.token
                const expiration = data.accessRequest.expirationTime
                return { token, expiration }
            } else if (permission === 'DENIED') {
                console.log('Access denied.')
                return null
            } else {
                console.log('Unknown permission state:', permission)
                return null
            }
        }
    }
}

async function getToken(serverUrl, clientId, description) {
    let tokenObj = await loadToken()
    if (tokenObj) {
        return tokenObj.token
    }
    // Request a new token
    return await requestToken(serverUrl, clientId, description)
}

module.exports = { getToken }
