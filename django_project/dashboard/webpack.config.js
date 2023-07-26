const path = require("path");
const BundleTracker = require('webpack-bundle-tracker');
const MiniCssExtractPlugin = require('mini-css-extract-plugin');
const { CleanWebpackPlugin } = require('clean-webpack-plugin'); // require clean-webpack-plugin
const ReactRefreshWebpackPlugin = require('@pmmmwh/react-refresh-webpack-plugin');
const webpack = require("webpack");

const mode = process.env.npm_lifecycle_script;
const isDev = (mode.includes('dev'));
const isServe = (mode.includes('serve'));
const filename = isDev ? "[name]" : "[name].[fullhash]";
const statsFilename = isDev ? './webpack-stats.dev.json' : './webpack-stats.prod.json';
const minimized = !isDev;

let conf = {
    entry: {
        App: './src/App.tsx'
    },
    output: {
        path: path.resolve(__dirname, "./bundles/dashboard"),
        filename: filename + '.js'
    },
    module: {
        rules: [
            {
                test: /\.tsx?$/,
                exclude: /node_modules/,
                use: [{ loader: 'ts-loader' }],
            },
            {
                test: /\.s[ac]ss$/i,
                use: [
                    MiniCssExtractPlugin.loader,
                    "css-loader",
                    "sass-loader"
                ],
            },
            {
                test: /\.css$/i,
                use: [
                    // Translates CSS into CommonJS
                    MiniCssExtractPlugin.loader, "css-loader",
                ],
            },
        ],
    },
    optimization: {
        minimize: minimized,
        splitChunks: {
            cacheGroups: {
                styles: {
                    name: "styles",
                    type: "css/mini-extract",
                    chunks: "all",
                    enforce: true,
                },
            },
        },
    },
    plugins: [
        new webpack.DefinePlugin({
          'process.env.NODE_DEBUG': JSON.stringify(process.env.NODE_DEBUG),
        }),
        new CleanWebpackPlugin(),
        new BundleTracker({ filename: statsFilename }),
        new MiniCssExtractPlugin({
            filename: filename + '.css',
            chunkFilename: filename + '.css',
            ignoreOrder: true,
        }),
    ],
    resolve: {
        modules: ['node_modules'],
        extensions: [".ts", ".tsx", ".js", ".css", ".scss"],
        fallback: {
            fs: false,
        }
    },
    watchOptions: {
        ignored: ['node_modules', './**/*.py'],
        aggregateTimeout: 300,
        poll: 1000
    }
};
if (isServe) {
    if (isDev) {
        conf['output'] = {
            path: path.resolve(__dirname, "./bundles/dashboard"),
            filename: filename + '.js',
            publicPath: 'http://localhost:9000/static/',
        }
    }
    conf['devServer'] = {
        hot: true,
        port: 9000,
        headers: {
            'Access-Control-Allow-Origin': '*'
        },
        devMiddleware: {
            writeToDisk: true,
        },
        allowedHosts: 'all',
        compress: true,
    }
    conf['output'] = {
        path: path.resolve(__dirname, "./bundles/dashboard"),
        filename: filename + '.js',
        publicPath: 'http://localhost:9000/static/',
    }
    conf['plugins'].push(
        new ReactRefreshWebpackPlugin()
    )
} else if (isDev) {
    conf['output'] = {
        path: path.resolve(__dirname, "./bundles/dashboard"),
        filename: filename + '.js'
    }
    conf['devServer'] = {
        hot: true,
        port: 9000
    }
}
module.exports = conf;
