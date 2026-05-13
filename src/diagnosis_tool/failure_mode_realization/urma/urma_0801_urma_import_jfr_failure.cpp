#include "urma_0801_urma_import_jfr_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0801UrmaImportJfrFailure> g_urma("urma_0801");

bool Urma0801UrmaImportJfrFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Token value must be set when token policy is not URMA_TOKEN_NONE."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0801UrmaImportJfrFailure::GetName() const
{
    return "urma_import_jfr 设置属性失败";
}

std::string Urma0801UrmaImportJfrFailure::GetRootCauseDesc() const
{
    return "资源操作失败，可能由于对象状态不匹配、参数非法、设备能力不支持或下游 provider/driver 返回错误；该路径返回 "
           "NULL";
}

RootCause Urma0801UrmaImportJfrFailure::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0801UrmaImportJfrFailure::GetFixSuggDesc() const
{
    return "UDMA错误定界；建链交换信息失败，可重试";
}

std::string Urma0801UrmaImportJfrFailure::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Token value must be set when token policy is not URMA_TOKEN_NONE.";
}

std::string Urma0801UrmaImportJfrFailure::GetId() const
{
    return "urma_0801";
}
} // namespace diag
