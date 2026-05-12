#include "urma_0798_urma_import_jetty_ex_invalid_param.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0798UrmaImportJettyExInvalidParam> g_urma("urma_0798");

bool Urma0798UrmaImportJettyExInvalidParam::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0798UrmaImportJettyExInvalidParam::GetName() const
{
    return "urma_import_jetty_ex 参数非法";
}

std::string Urma0798UrmaImportJettyExInvalidParam::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `ctx == NULL || rjetty == NULL || token_value == NULL || cfg == "
           "NULL`；该路径返回 NULL";
}

RootCause Urma0798UrmaImportJettyExInvalidParam::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0798UrmaImportJettyExInvalidParam::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0798UrmaImportJettyExInvalidParam::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter.";
}

std::string Urma0798UrmaImportJettyExInvalidParam::GetId() const
{
    return "urma_0798";
}
} // namespace diag
