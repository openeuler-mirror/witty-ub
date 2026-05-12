#include "urma_0134_bondp_delete_jfc_resource_delete_failure_use_cnt_0.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0134BondpDeleteJfcResourceDeleteFailureUseCnt0> g_urma("urma_0134");

bool Urma0134BondpDeleteJfcResourceDeleteFailureUseCnt0::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to delete jfc[%], still in use. use_cnt: %"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0134BondpDeleteJfcResourceDeleteFailureUseCnt0::GetName() const
{
    return "bondp_delete_jfc 删除资源失败（use_cnt > 0）";
}

std::string Urma0134BondpDeleteJfcResourceDeleteFailureUseCnt0::GetRootCauseDesc() const
{
    return "资源操作失败，可能由于对象状态不匹配、参数非法、设备能力不支持或下游 provider/driver 返回错误；该路径返回 "
           "URMA_EAGAIN";
}

RootCause Urma0134BondpDeleteJfcResourceDeleteFailureUseCnt0::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0134BondpDeleteJfcResourceDeleteFailureUseCnt0::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0134BondpDeleteJfcResourceDeleteFailureUseCnt0::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to delete jfc[%], still in use. use_cnt: %";
}

std::string Urma0134BondpDeleteJfcResourceDeleteFailureUseCnt0::GetId() const
{
    return "urma_0134";
}
} // namespace diag
