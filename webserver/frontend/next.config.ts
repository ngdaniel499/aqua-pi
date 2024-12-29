import { NextConfig } from 'next'

const config: NextConfig = {
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'https://aquapidata.duckdns.org/api/:path*'
      },
      {
        source: '/upload',
        destination: 'https://aquapidata.duckdns.org/upload'
      }
    ]
  }
}

export default config