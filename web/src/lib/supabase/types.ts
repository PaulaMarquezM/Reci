// Generado manualmente desde el schema v1.
// Para regenerar desde Supabase: npx supabase gen types typescript --project-id gvvnnijxwfuetjegctiy > src/lib/supabase/types.ts

export type MaterialType = 'vidrio' | 'plastico' | 'desconocido'
export type RobotStatus = 'idle' | 'moving' | 'charging'
export type CallStatus = 'pending' | 'in_progress' | 'resolved' | 'cancelled'

export interface Database {
  public: {
    Tables: {
      profiles: {
        Row: {
          id: string
          display_name: string | null
          avatar_url: string | null
          facial_opt_in: boolean
          total_points: number
          created_at: string
          updated_at: string
        }
        Insert: {
          id: string
          display_name?: string | null
          avatar_url?: string | null
          facial_opt_in?: boolean
          total_points?: number
          created_at?: string
          updated_at?: string
        }
        Update: {
          id?: string
          display_name?: string | null
          avatar_url?: string | null
          facial_opt_in?: boolean
          total_points?: number
          created_at?: string
          updated_at?: string
        }
        Relationships: []
      }
      recycle_events: {
        Row: {
          id: string
          user_id: string | null
          material: MaterialType
          confidence: number | null
          robot_point_id: string | null
          claim_code: string | null
          claim_expires_at: string | null
          claimed_at: string | null
          created_at: string
        }
        Insert: {
          id?: string
          user_id?: string | null
          material: MaterialType
          confidence?: number | null
          robot_point_id?: string | null
          claim_code?: string | null
          claim_expires_at?: string | null
          claimed_at?: string | null
          created_at?: string
        }
        Update: {
          id?: string
          user_id?: string | null
          material?: MaterialType
          confidence?: number | null
          robot_point_id?: string | null
          claim_code?: string | null
          claim_expires_at?: string | null
          claimed_at?: string | null
          created_at?: string
        }
        Relationships: []
      }
      points_ledger: {
        Row: {
          id: string
          user_id: string
          delta: number
          reason: string
          event_id: string | null
          created_at: string
        }
        Insert: {
          id?: string
          user_id: string
          delta: number
          reason: string
          event_id?: string | null
          created_at?: string
        }
        Update: {
          id?: string
          user_id?: string
          delta?: number
          reason?: string
          event_id?: string | null
          created_at?: string
        }
        Relationships: []
      }
      streaks: {
        Row: {
          user_id: string
          current_streak: number
          longest_streak: number
          last_recycle_at: string | null
          updated_at: string
        }
        Insert: {
          user_id: string
          current_streak?: number
          longest_streak?: number
          last_recycle_at?: string | null
          updated_at?: string
        }
        Update: {
          user_id?: string
          current_streak?: number
          longest_streak?: number
          last_recycle_at?: string | null
          updated_at?: string
        }
        Relationships: []
      }
      coupons: {
        Row: {
          id: string
          title: string
          description: string | null
          cost_points: number
          stock: number
          active: boolean
          created_at: string
        }
        Insert: {
          id?: string
          title: string
          description?: string | null
          cost_points: number
          stock?: number
          active?: boolean
          created_at?: string
        }
        Update: {
          id?: string
          title?: string
          description?: string | null
          cost_points?: number
          stock?: number
          active?: boolean
          created_at?: string
        }
        Relationships: []
      }
      coupon_redemptions: {
        Row: {
          id: string
          user_id: string
          coupon_id: string
          code: string
          redeemed_at: string
        }
        Insert: {
          id?: string
          user_id: string
          coupon_id: string
          code?: string
          redeemed_at?: string
        }
        Update: {
          id?: string
          user_id?: string
          coupon_id?: string
          code?: string
          redeemed_at?: string
        }
        Relationships: []
      }
      robot_points: {
        Row: {
          id: string
          name: string
          lat: number
          lng: number
          notes: string | null
          active: boolean
          created_at: string
        }
        Insert: {
          id?: string
          name: string
          lat: number
          lng: number
          notes?: string | null
          active?: boolean
          created_at?: string
        }
        Update: {
          id?: string
          name?: string
          lat?: number
          lng?: number
          notes?: string | null
          active?: boolean
          created_at?: string
        }
        Relationships: []
      }
      robot_positions: {
        Row: {
          id: string
          robot_id: string
          point_id: string | null
          lat: number
          lng: number
          status: RobotStatus
          recorded_at: string
        }
        Insert: {
          id?: string
          robot_id?: string
          point_id?: string | null
          lat: number
          lng: number
          status?: RobotStatus
          recorded_at?: string
        }
        Update: {
          id?: string
          robot_id?: string
          point_id?: string | null
          lat?: number
          lng?: number
          status?: RobotStatus
          recorded_at?: string
        }
        Relationships: []
      }
      compartments: {
        Row: {
          id: 'vidrio' | 'plastico'
          fill_percent: number
          last_updated: string
          last_emptied_at: string | null
        }
        Insert: {
          id: 'vidrio' | 'plastico'
          fill_percent?: number
          last_updated?: string
          last_emptied_at?: string | null
        }
        Update: {
          id?: 'vidrio' | 'plastico'
          fill_percent?: number
          last_updated?: string
          last_emptied_at?: string | null
        }
        Relationships: []
      }
      call_requests: {
        Row: {
          id: string
          user_id: string
          point_id: string
          status: CallStatus
          created_at: string
          resolved_at: string | null
        }
        Insert: {
          id?: string
          user_id: string
          point_id: string
          status?: CallStatus
          created_at?: string
          resolved_at?: string | null
        }
        Update: {
          id?: string
          user_id?: string
          point_id?: string
          status?: CallStatus
          created_at?: string
          resolved_at?: string | null
        }
        Relationships: []
      }
      face_embeddings: {
        Row: {
          user_id: string
          storage_path: string | null
          consent_signed_at: string
          embedding_ciphertext: string | null
          model: string | null
          embedding_version: number
        }
        Insert: {
          user_id: string
          storage_path?: string | null
          consent_signed_at?: string
          embedding_ciphertext?: string | null
          model?: string | null
          embedding_version?: number
        }
        Update: {
          user_id?: string
          storage_path?: string | null
          consent_signed_at?: string
          embedding_ciphertext?: string | null
          model?: string | null
          embedding_version?: number
        }
        Relationships: []
      }
      push_tokens: {
        Row: {
          id: string
          user_id: string
          endpoint: string
          keys: Record<string, string>
          created_at: string
        }
        Insert: {
          id?: string
          user_id: string
          endpoint: string
          keys: Record<string, string>
          created_at?: string
        }
        Update: {
          id?: string
          user_id?: string
          endpoint?: string
          keys?: Record<string, string>
          created_at?: string
        }
        Relationships: []
      }
    }
    Views: Record<string, never>
    Functions: Record<string, never>
    Enums: {
      material_type: MaterialType
      robot_status: RobotStatus
      call_status: CallStatus
    }
    CompositeTypes: Record<string, never>
  }
}
