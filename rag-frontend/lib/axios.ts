import axios from "axios"

const baseURL =
  process.env.NEXT_PUBLIC_BACKEND_URL && process.env.NODE_ENV === "production"
    ? process.env.NEXT_PUBLIC_BACKEND_URL
    : "http://localhost:8000"

const axiosInstance = axios.create({
  baseURL,
})

export default axiosInstance