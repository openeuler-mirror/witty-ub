#include "urma_0795_urma_import_jetty_async_invalid_param.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0795UrmaImportJettyAsyncInvalidParam> g_urma("urma_0795");

bool Urma0795UrmaImportJettyAsyncInvalidParam::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0795UrmaImportJettyAsyncInvalidParam::GetName() const
{
    return "urma_import_jetty_async 参数非法";
}

std::string Urma0795UrmaImportJettyAsyncInvalidParam::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `notifier == NULL || notifier->urma_ctx == NULL || rjetty == NULL || "
           "token_value == NULL`；该路径返回 NULL";
}

RootCause Urma0795UrmaImportJettyAsyncInvalidParam::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0795UrmaImportJettyAsyncInvalidParam::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0795UrmaImportJettyAsyncInvalidParam::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter.";
}

std::string Urma0795UrmaImportJettyAsyncInvalidParam::GetId() const
{
    return "urma_0795";
}
} // namespace diag
