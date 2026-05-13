#include "urma_0793_urma_import_jetty_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0793UrmaImportJettyFailure> g_urma("urma_0793");

bool Urma0793UrmaImportJettyFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Token value must be set when token policy is not URMA_TOKEN_NONE."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0793UrmaImportJettyFailure::GetName() const
{
    return "urma_import_jetty 设置属性失败";
}

std::string Urma0793UrmaImportJettyFailure::GetRootCauseDesc() const
{
    return "资源操作失败，可能由于对象状态不匹配、参数非法、设备能力不支持或下游 provider/driver 返回错误；该路径返回 "
           "NULL";
}

RootCause Urma0793UrmaImportJettyFailure::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0793UrmaImportJettyFailure::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0793UrmaImportJettyFailure::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Token value must be set when token policy is not URMA_TOKEN_NONE.";
}

std::string Urma0793UrmaImportJettyFailure::GetId() const
{
    return "urma_0793";
}
} // namespace diag
