#include "urma_0029_bondp_uninit_resource_delete_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0029BondpUninitResourceDeleteFailure> g_urma("urma_0029");

bool Urma0029BondpUninitResourceDeleteFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to delete global context."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0029BondpUninitResourceDeleteFailure::GetName() const
{
    return "bondp_uninit 删除资源失败";
}

std::string Urma0029BondpUninitResourceDeleteFailure::GetRootCauseDesc() const
{
    return "资源操作失败，可能由于对象状态不匹配、参数非法、设备能力不支持或下游 provider/driver 返回错误；该路径返回 "
           "URMA_FAIL";
}

RootCause Urma0029BondpUninitResourceDeleteFailure::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0029BondpUninitResourceDeleteFailure::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0029BondpUninitResourceDeleteFailure::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to delete global context.";
}

std::string Urma0029BondpUninitResourceDeleteFailure::GetId() const
{
    return "urma_0029";
}
} // namespace diag
