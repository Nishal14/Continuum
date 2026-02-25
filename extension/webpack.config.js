const path = require('path');
const CopyPlugin = require('copy-webpack-plugin');
const HtmlWebpackPlugin = require('html-webpack-plugin');

module.exports = {
  entry: {
    contentScript: './src/content/contentScript.ts',
    background: './src/background/background.ts',
    sidebar: './src/sidebar/index.tsx'
  },
  output: {
    path: path.resolve(__dirname, 'dist'),
    filename: '[name].js'
  },
  module: {
    rules: [
      {
        test: /\.tsx?$/,
        use: 'ts-loader',
        exclude: /node_modules/
      }
    ]
  },
  resolve: {
    extensions: ['.ts', '.tsx', '.js', '.jsx']
  },
  plugins: [
    new CopyPlugin({
      patterns: [
        { from: 'manifest.json', to: 'manifest.json' },
        { from: 'logo.png', to: 'logo.png' }
      ]
    }),
    new HtmlWebpackPlugin({
      template: './src/sidebar/popup.html',
      filename: 'popup.html',
      chunks: ['sidebar']
    })
  ]
};
