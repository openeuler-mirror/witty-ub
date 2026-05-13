#include "urma_0568_urma_cmd_unimport_jetty_invalid_param.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0568UrmaCmdUnimportJettyInvalidParam> g_urma("urma_0568");

bool Urma0568UrmaCmdUnimportJettyInvalidParam::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0568UrmaCmdUnimportJettyInvalidParam::GetName() const
{
    return "urma_cmd_unimport_jetty 参数非法";
}

std::string Urma0568UrmaCmdUnimportJettyInvalidParam::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `tjetty == NULL`；该路径返回 -1";
}

RootCause Urma0568UrmaCmdUnimportJettyInvalidParam::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0568UrmaCmdUnimportJettyInvalidParam::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0568UrmaCmdUnimportJettyInvalidParam::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter";
}

std::string Urma0568UrmaCmdUnimportJettyInvalidParam::GetId() const
{
    return "urma_0568";
}
} // namespace diag
