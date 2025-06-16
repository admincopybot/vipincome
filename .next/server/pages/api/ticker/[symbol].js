"use strict";(()=>{var t={};t.id=748,t.ids=[748],t.modules={2554:(t,e,r)=>{r.a(t,async(t,n)=>{try{r.r(e),r.d(e,{default:()=>a});var s=r(9866),o=r(8152),i=t([s]);async function a(t,e){if("GET"!==t.method)return e.status(405).json({error:"Method not allowed"});if(!(0,o.wR)(t))return e.status(401).json({error:"Unauthorized"});let{symbol:r}=t.query;if(!r||"string"!=typeof r)return e.status(400).json({error:"Invalid symbol"});try{let t=await (0,s.k7)(r);if(!t)return e.status(404).json({error:"Ticker not found"});return e.status(200).json(t)}catch(t){return console.error("Database error:",t),e.status(500).json({error:"Internal server error"})}}s=(i.then?(await i)():i)[0],n()}catch(t){n(t)}})},3480:(t,e,r)=>{t.exports=r(5600)},3558:(t,e,r)=>{r.a(t,async(t,n)=>{try{r.r(e),r.d(e,{config:()=>u,default:()=>c,routeModule:()=>_});var s=r(3480),o=r(8667),i=r(6435),a=r(2554),d=t([a]);a=(d.then?(await d)():d)[0];let c=(0,i.M)(a,"default"),u=(0,i.M)(a,"config"),_=new s.PagesAPIRouteModule({definition:{kind:o.A.PAGES_API,page:"/api/ticker/[symbol]",pathname:"/api/ticker/[symbol]",bundlePath:"",filename:""},userland:a});n()}catch(t){n(t)}})},4939:t=>{t.exports=import("pg")},5600:t=>{t.exports=require("next/dist/compiled/next-server/pages-api.runtime.prod.js")},6435:(t,e)=>{Object.defineProperty(e,"M",{enumerable:!0,get:function(){return function t(e,r){return r in e?e[r]:"then"in e&&"function"==typeof e.then?e.then(e=>t(e,r)):"function"==typeof e&&"default"===r?e:void 0}}})},8152:(t,e,r)=>{r.d(e,{wR:()=>i});let n=require("jsonwebtoken");var s=r.n(n);let o=`-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA4f5wg5l2hKsTeNem/V41
fGnJm6gOdrj8ym3rFkEjWT2btf06kkstX0BdVqKyGJm7TQsLt3nLDj9dxKwNsU0f
Vp4H3VHZrQNxVOgB2wG6dRkj7w+7QbqMTBJfEVUhkE9g0fOhp9Xg4GdO8g7N1qPb
f8n0WzGLWVFT5XPTfp5PaO3F6Q8Z5g5v1p4A2O4F8DQ8+P6K+N9w6zKtW5f6qW8x
f+bT7I7KqGbTr2XM7A3t0vOj5VRe8VQ7kK7Af6z8hD2L9Rg6K5z8X7g0+hWJn5zE
YOJr7qFzO5zRoE8TI6L8c4aZ6Eq2G6yKo8Y5J7cxW1yV+Q+p9zKJ9nK7p1Q2ov5X
QIDAQAB
-----END PUBLIC KEY-----`;function i(t){let e=function(t){let e=t.headers.authorization;return e&&e.startsWith("Bearer ")?e.substring(7):null}(t);if(!e)return null;try{return s().verify(e,o,{algorithms:["RS256"],issuer:void 0,audience:void 0})}catch(t){return console.error("JWT validation failed:",t),null}}},8667:(t,e)=>{Object.defineProperty(e,"A",{enumerable:!0,get:function(){return r}});var r=function(t){return t.PAGES="PAGES",t.PAGES_API="PAGES_API",t.APP_PAGE="APP_PAGE",t.APP_ROUTE="APP_ROUTE",t.IMAGE="IMAGE",t}({})},9866:(t,e,r)=>{r.a(t,async(t,n)=>{try{r.d(e,{EL:()=>a,P:()=>c,k7:()=>d});var s=r(4939),o=t([s]);s=(o.then?(await o)():o)[0];let u=null;function i(){return u||(u=new s.Pool({connectionString:"postgresql://neondb_owner:npg_nwv0MhqyR3ez@ep-holy-shadow-a6fuu2s3.us-west-2.aws.neon.tech/neondb?sslmode=require",ssl:{rejectUnauthorized:!1}})),u}async function a(){let t=i(),e=`
    SELECT 
      symbol, current_price, score,
      trend1_pass, trend1_current, trend1_threshold, trend1_description,
      trend2_pass, trend2_current, trend2_threshold, trend2_description,
      snapback_pass, snapback_current, snapback_threshold, snapback_description,
      momentum_pass, momentum_current, momentum_threshold, momentum_description,
      stabilizing_pass, stabilizing_current, stabilizing_threshold, stabilizing_description,
      trading_volume, options_contracts_10_42_dte, last_updated
    FROM etf_scores 
    ORDER BY 
      score DESC,
      options_contracts_10_42_dte DESC,
      trading_volume DESC,
      symbol ASC
  `;return(await t.query(e)).rows}async function d(t){let e=i(),r=`
    SELECT 
      symbol, current_price, score,
      trend1_pass, trend1_current, trend1_threshold, trend1_description,
      trend2_pass, trend2_current, trend2_threshold, trend2_description,
      snapback_pass, snapback_current, snapback_threshold, snapback_description,
      momentum_pass, momentum_current, momentum_threshold, momentum_description,
      stabilizing_pass, stabilizing_current, stabilizing_threshold, stabilizing_description,
      trading_volume, options_contracts_10_42_dte, last_updated
    FROM etf_scores 
    WHERE symbol = $1
  `;return(await e.query(r,[t.toUpperCase()])).rows[0]||null}async function c(t="",e=50){let r=i(),n=`
    SELECT 
      symbol, current_price, score,
      trend1_pass, trend1_current, trend1_threshold, trend1_description,
      trend2_pass, trend2_current, trend2_threshold, trend2_description,
      snapback_pass, snapback_current, snapback_threshold, snapback_description,
      momentum_pass, momentum_current, momentum_threshold, momentum_description,
      stabilizing_pass, stabilizing_current, stabilizing_threshold, stabilizing_description,
      trading_volume, options_contracts_10_42_dte, last_updated
    FROM etf_scores 
    WHERE symbol ILIKE $1
    ORDER BY 
      score DESC,
      options_contracts_10_42_dte DESC,
      trading_volume DESC,
      symbol ASC
    LIMIT $2
  `;return(await r.query(n,[`%${t.toUpperCase()}%`,e])).rows}n()}catch(t){n(t)}})}};var e=require("../../../webpack-api-runtime.js");e.C(t);var r=e(e.s=3558);module.exports=r})();