#include "urma_0570_urma_cmd_unimport_jetty_async_invalid_param.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0570UrmaCmdUnimportJettyAsyncInvalidParam> g_urma("urma_0570");

bool Urma0570UrmaCmdUnimportJettyAsyncInvalidParam::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0570UrmaCmdUnimportJettyAsyncInvalidParam::GetName() const
{
    return "urma_cmd_unimport_jetty_async 参数非法";
}

std::string Urma0570UrmaCmdUnimportJettyAsyncInvalidParam::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `tjetty == NULL`；该路径返回 -1";
}

RootCause Urma0570UrmaCmdUnimportJettyAsyncInvalidParam::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0570UrmaCmdUnimportJettyAsyncInvalidParam::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0570UrmaCmdUnimportJettyAsyncInvalidParam::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter";
}

std::string Urma0570UrmaCmdUnimportJettyAsyncInvalidParam::GetId() const
{
    return "urma_0570";
}
} // namespace diag
