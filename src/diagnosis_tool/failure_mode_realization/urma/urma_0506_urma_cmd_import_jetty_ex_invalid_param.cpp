#include "urma_0506_urma_cmd_import_jetty_ex_invalid_param.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0506UrmaCmdImportJettyExInvalidParam> g_urma("urma_0506");

bool Urma0506UrmaCmdImportJettyExInvalidParam::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0506UrmaCmdImportJettyExInvalidParam::GetName() const
{
    return "urma_cmd_import_jetty_ex 参数非法";
}

std::string Urma0506UrmaCmdImportJettyExInvalidParam::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `ctx == NULL || ctx->dev_fd < 0 || tjetty == NULL || cfg == NULL || "
           "cfg->token == NULL || ex_cfg == N`；该路径返回 -1";
}

RootCause Urma0506UrmaCmdImportJettyExInvalidParam::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0506UrmaCmdImportJettyExInvalidParam::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0506UrmaCmdImportJettyExInvalidParam::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter";
}

std::string Urma0506UrmaCmdImportJettyExInvalidParam::GetId() const
{
    return "urma_0506";
}
} // namespace diag
