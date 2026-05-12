#include "urma_1038_urma_import_seg_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma1038UrmaImportSegFailure> g_urma("urma_1038");

bool Urma1038UrmaImportSegFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Token value must be set when token policy is not URMA_TOKEN_NONE."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma1038UrmaImportSegFailure::GetName() const
{
    return "urma_import_seg 设置属性失败";
}

std::string Urma1038UrmaImportSegFailure::GetRootCauseDesc() const
{
    return "资源操作失败，可能由于对象状态不匹配、参数非法、设备能力不支持或下游 provider/driver 返回错误；该路径返回 "
           "NULL";
}

RootCause Urma1038UrmaImportSegFailure::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma1038UrmaImportSegFailure::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma1038UrmaImportSegFailure::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Token value must be set when token policy is not URMA_TOKEN_NONE.";
}

std::string Urma1038UrmaImportSegFailure::GetId() const
{
    return "urma_1038";
}
} // namespace diag
