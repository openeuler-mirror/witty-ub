#include "urma_0754_urma_flush_jetty_invalid_param.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0754UrmaFlushJettyInvalidParam> g_urma("urma_0754");

bool Urma0754UrmaFlushJettyInvalidParam::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0754UrmaFlushJettyInvalidParam::GetName() const
{
    return "urma_flush_jetty 参数非法";
}

std::string Urma0754UrmaFlushJettyInvalidParam::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `jetty == NULL || cr == NULL || cr_cnt <= 0 || (uint32_t)cr_cnt > "
           "jetty->jetty_cfg.jfs_cfg.depth`；该路径返回 (int)(-URMA_EINVAL)";
}

RootCause Urma0754UrmaFlushJettyInvalidParam::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0754UrmaFlushJettyInvalidParam::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0754UrmaFlushJettyInvalidParam::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter.";
}

std::string Urma0754UrmaFlushJettyInvalidParam::GetId() const
{
    return "urma_0754";
}
} // namespace diag
