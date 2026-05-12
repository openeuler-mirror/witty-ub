#include "urma_0861_urma_unimport_jetty_async_import_jetty_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0861UrmaUnimportJettyAsyncImportJettyFailure> g_urma("urma_0861");

bool Urma0861UrmaUnimportJettyAsyncImportJettyFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to unimport jetty."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0861UrmaUnimportJettyAsyncImportJettyFailure::GetName() const
{
    return "urma_unimport_jetty_async 导入Jetty失败";
}

std::string Urma0861UrmaUnimportJettyAsyncImportJettyFailure::GetRootCauseDesc() const
{
    return "资源操作失败，可能由于对象状态不匹配、参数非法、设备能力不支持或下游 provider/driver 返回错误；该路径返回 "
           "status";
}

RootCause Urma0861UrmaUnimportJettyAsyncImportJettyFailure::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0861UrmaUnimportJettyAsyncImportJettyFailure::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0861UrmaUnimportJettyAsyncImportJettyFailure::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to unimport jetty.";
}

std::string Urma0861UrmaUnimportJettyAsyncImportJettyFailure::GetId() const
{
    return "urma_0861";
}
} // namespace diag
