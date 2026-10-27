import axios from "axios";
import { useEffect, useState } from "react";
import api from "./api";

const api = axios.create({
  baseURL: "http://127.0.0.1:8000",
  headers: {
    "Content-Type": "application/json",
  },
});

export default Api;

