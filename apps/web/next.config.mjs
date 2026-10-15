/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  transpilePackages: ["@sci/shared"],
  webpack: (config) => {
    // WalletConnect / MetaMask SDK optional deps that don't exist in the browser.
    config.externals.push("pino-pretty", "lokijs", "encoding");
    config.resolve.alias = {
      ...config.resolve.alias,
      "@react-native-async-storage/async-storage": false,
      // Pulled in by @coinbase/cdp-sdk (via wagmi's Base Account connector) for x402 payments,
      // which this app never uses; the packages are optional and not installed.
      "@x402/core/client": false,
      "@x402/evm": false,
      "@x402/evm/exact/client": false,
      "@x402/evm/upto/client": false,
      "@x402/svm/exact/client": false,
    };
    return config;
  },
};

export default nextConfig;
