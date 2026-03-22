import {
  boolean,
  index,
  integer,
  jsonb,
  pgTable,
  serial,
  text,
  timestamp,
  uuid,
} from "drizzle-orm/pg-core";

export const users = pgTable("users", {
  id: serial("id").primaryKey(),
  email: text("email").notNull().unique(),
  passwordHash: text("password_hash").notNull(),
  createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
  galleryPublic: boolean("gallery_public").notNull().default(false),
});

export const userBackgrounds = pgTable(
  "user_backgrounds",
  {
    id: uuid("id").defaultRandom().primaryKey(),
    userId: integer("user_id")
      .notNull()
      .references(() => users.id, { onDelete: "cascade" }),
    storageKey: text("storage_key").notNull(),
    originalFilename: text("original_filename").notNull(),
    createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
  },
  (t) => [index("user_backgrounds_user_id_idx").on(t.userId)],
);

export const generations = pgTable(
  "generations",
  {
    id: uuid("id").defaultRandom().primaryKey(),
    userId: integer("user_id").references(() => users.id, { onDelete: "set null" }),
    jobUid: text("job_uid").notNull().unique(),
    outputKey: text("output_key").notNull(),
    outputFormat: text("output_format").notNull(),
    topic: text("topic"),
    dialogue: jsonb("dialogue").notNull().$type<{ speaker: string; text: string }[]>(),
    bgSource: text("bg_source"),
    createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
  },
  (t) => [index("generations_user_id_idx").on(t.userId)],
);
