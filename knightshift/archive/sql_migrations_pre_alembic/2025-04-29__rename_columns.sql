-- Rename columns in tv_channel_games
ALTER TABLE tv_channel_games RENAME COLUMN id TO id_game;
ALTER TABLE tv_channel_games RENAME COLUMN event TO val_event_name;
ALTER TABLE tv_channel_games RENAME COLUMN site TO val_site_url;
ALTER TABLE tv_channel_games RENAME COLUMN date TO dt_game;
ALTER TABLE tv_channel_games RENAME COLUMN white TO id_user_white;
ALTER TABLE tv_channel_games RENAME COLUMN black TO id_user_black;
ALTER TABLE tv_channel_games RENAME COLUMN result TO val_result;
ALTER TABLE tv_channel_games RENAME COLUMN utc_date TO dt_utc_game_date;
ALTER TABLE tv_channel_games RENAME COLUMN utc_time TO tm_utc_game_start;
ALTER TABLE tv_channel_games RENAME COLUMN white_elo TO val_elo_white;
ALTER TABLE tv_channel_games RENAME COLUMN black_elo TO val_elo_black;
ALTER TABLE tv_channel_games RENAME COLUMN white_title TO val_title_white;
ALTER TABLE tv_channel_games RENAME COLUMN black_title TO val_title_black;
ALTER TABLE tv_channel_games RENAME COLUMN variant TO val_variant;
ALTER TABLE tv_channel_games RENAME COLUMN time_control TO val_time_control;
ALTER TABLE tv_channel_games RENAME COLUMN eco TO val_opening_eco_code;
ALTER TABLE tv_channel_games RENAME COLUMN termination TO val_termination;
ALTER TABLE tv_channel_games RENAME COLUMN moves TO val_moves_pgn;
ALTER TABLE tv_channel_games RENAME COLUMN is_validated TO ind_validated;
ALTER TABLE tv_channel_games RENAME COLUMN opening TO val_opening_name;
ALTER TABLE tv_channel_games RENAME COLUMN profile_updated TO ind_profile_updated;
ALTER TABLE tv_channel_games RENAME COLUMN ingested_at TO tm_ingested;
ALTER TABLE tv_channel_games RENAME COLUMN validation_notes TO val_validation_notes;

-- Rename columns in lichess_users
ALTER TABLE lichess_users RENAME COLUMN id TO id_user;
ALTER TABLE lichess_users RENAME COLUMN title TO val_title;
ALTER TABLE lichess_users RENAME COLUMN url TO val_profile_url;
ALTER TABLE lichess_users RENAME COLUMN real_name TO val_name;
ALTER TABLE lichess_users RENAME COLUMN location TO val_location;
ALTER TABLE lichess_users RENAME COLUMN bio TO val_bio_text;
ALTER TABLE lichess_users RENAME COLUMN fide_rating TO val_fide_rating;
ALTER TABLE lichess_users RENAME COLUMN uscf_rating TO val_uscf_rating;
ALTER TABLE lichess_users RENAME COLUMN bullet_rating TO val_rating_bullet;
ALTER TABLE lichess_users RENAME COLUMN blitz_rating TO val_rating_blitz;
ALTER TABLE lichess_users RENAME COLUMN classical_rating TO val_rating_classical;
ALTER TABLE lichess_users RENAME COLUMN rapid_rating TO val_rating_rapid;
ALTER TABLE lichess_users RENAME COLUMN chess960_rating TO val_rating_960;
ALTER TABLE lichess_users RENAME COLUMN ultra_bullet_rating TO val_rating_ultrabullet;
ALTER TABLE lichess_users RENAME COLUMN country_code TO val_country_code;
ALTER TABLE lichess_users RENAME COLUMN created_at TO tm_created;
ALTER TABLE lichess_users RENAME COLUMN seen_at TO tm_last_seen;
ALTER TABLE lichess_users RENAME COLUMN playtime_total TO amt_playtime_total;
ALTER TABLE lichess_users RENAME COLUMN playtime_tv TO amt_playtime_tv;
ALTER TABLE lichess_users RENAME COLUMN games_all TO n_games_all;
ALTER TABLE lichess_users RENAME COLUMN games_rated TO n_games_rated;
ALTER TABLE lichess_users RENAME COLUMN games_win TO n_games_win;
ALTER TABLE lichess_users RENAME COLUMN games_loss TO n_games_loss;
ALTER TABLE lichess_users RENAME COLUMN games_draw TO n_games_draw;
ALTER TABLE lichess_users RENAME COLUMN patron TO ind_is_patron;
ALTER TABLE lichess_users RENAME COLUMN streaming TO ind_is_streaming;
