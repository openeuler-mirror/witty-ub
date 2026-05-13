#include "urma_0858_urma_unimport_jetty_invalid_param.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0858UrmaUnimportJettyInvalidParam> g_urma("urma_0858");

bool Urma0858UrmaUnimportJettyInvalidParam::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0858UrmaUnimportJettyInvalidParam::GetName() const
{
    return "urma_unimport_jetty 参数非法";
}

std::string Urma0858UrmaUnimportJettyInvalidParam::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `tjetty == NULL`；该路径返回 URMA_EINVAL";
}

RootCause Urma0858UrmaUnimportJettyInvalidParam::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0858UrmaUnimportJettyInvalidParam::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0858UrmaUnimportJettyInvalidParam::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter.";
}

std::string Urma0858UrmaUnimportJettyInvalidParam::GetId() const
{
    return "urma_0858";
}
} // namespace diag
