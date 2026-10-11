--
-- PostgreSQL database dump
--

\restrict AF9ykreUxugsrCaUr9e0r239IZfcKDLo7iH0QaojAKkFtRlgsGSvyobQnXQfCeg

-- Dumped from database version 16.15
-- Dumped by pg_dump version 16.15

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: scan_histories; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.scan_histories (
    id uuid NOT NULL,
    user_id uuid NOT NULL,
    image_url character varying NOT NULL,
    detected_objects json NOT NULL,
    danger_level character varying,
    is_recyclable boolean,
    insight_summary character varying,
    full_insight_data json,
    created_at timestamp with time zone NOT NULL
);


--
-- Name: users; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.users (
    id uuid NOT NULL,
    google_id character varying NOT NULL,
    email character varying NOT NULL,
    name character varying NOT NULL,
    avatar_url character varying,
    created_at timestamp with time zone NOT NULL
);


--
-- Name: scan_histories scan_histories_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.scan_histories
    ADD CONSTRAINT scan_histories_pkey PRIMARY KEY (id);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: ix_scan_histories_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_scan_histories_user_id ON public.scan_histories USING btree (user_id);


--
-- Name: ix_users_email; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_users_email ON public.users USING btree (email);


--
-- Name: ix_users_google_id; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_users_google_id ON public.users USING btree (google_id);


--
-- Name: scan_histories scan_histories_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.scan_histories
    ADD CONSTRAINT scan_histories_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- PostgreSQL database dump complete
--

\unrestrict AF9ykreUxugsrCaUr9e0r239IZfcKDLo7iH0QaojAKkFtRlgsGSvyobQnXQfCeg

