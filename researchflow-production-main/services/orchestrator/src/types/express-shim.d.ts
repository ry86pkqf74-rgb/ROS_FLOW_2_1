/**
 * Express type re-exports for ESM compatibility
 * 
 * This shim allows named imports like:
 * import { Router, Request, Response } from 'express';
 * 
 * Which would otherwise fail because @types/express uses
 * the declare namespace pattern.
 */

import * as core from 'express-serve-static-core';
import bodyParser = require('body-parser');
import serveStatic = require('serve-static');

declare function express(): core.Express;

declare namespace express {
  const json: typeof bodyParser.json;
  const raw: typeof bodyParser.raw;
  const text: typeof bodyParser.text;
  const urlencoded: typeof bodyParser.urlencoded;
  const static: serveStatic.RequestHandlerConstructor<core.Response>;

  const application: core.Application;
  const request: core.Request;
  const response: core.Response;

  type Application = core.Express;

  function Router(options?: core.RouterOptions): core.Router;
}

declare module 'express' {
  export default express;
  export { express };

  export const Router: typeof express.Router;
  export const json: typeof express.json;
  export const raw: typeof express.raw;
  export const text: typeof express.text;
  export const urlencoded: typeof express.urlencoded;
  export const static: typeof express.static;
  export const application: typeof express.application;
  export const request: typeof express.request;
  export const response: typeof express.response;

  // Re-export types that are in the namespace as module-level exports
  export type Request<
    P = core.ParamsDictionary,
    ResBody = any,
    ReqBody = any,
    ReqQuery = core.Query,
    Locals extends Record<string, any> = Record<string, any>
  > = core.Request<P, ResBody, ReqBody, ReqQuery, Locals>;

  export type Response<
    ResBody = any,
    Locals extends Record<string, any> = Record<string, any>
  > = core.Response<ResBody, Locals>;

  export type NextFunction = core.NextFunction;
  export type RequestHandler<
    P = core.ParamsDictionary,
    ResBody = any,
    ReqBody = any,
    ReqQuery = core.Query,
    Locals extends Record<string, any> = Record<string, any>
  > = core.RequestHandler<P, ResBody, ReqBody, ReqQuery, Locals>;

  export type ErrorRequestHandler<
    P = core.ParamsDictionary,
    ResBody = any,
    ReqBody = any,
    ReqQuery = core.Query,
    Locals extends Record<string, any> = Record<string, any>
  > = core.ErrorRequestHandler<P, ResBody, ReqBody, ReqQuery, Locals>;

  export type Application = core.Application;
  export type Express = core.Express;
  export type Router = core.Router;
}
