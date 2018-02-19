def setup(bot):
    from .quotes import Quotes
    bot.add_cog(Quotes(bot))
