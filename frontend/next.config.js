/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  swcMinify: true,
  transpilePackages: ['three'],
  webpack: (config) => {
    config.externals.push({
      'plotly.js': 'plotly.js'
    });
    return config;
  }
}

module.exports = nextConfig
