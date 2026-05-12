#include "urma_0465_urma_cmd_free_jfc_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0465UrmaCmdFreeJfcFailure> g_urma("urma_0465");

bool Urma0465UrmaCmdFreeJfcFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {
        "There is jfc event and it must be acked, jfc_comp:%, comp:%, jfc_async:%, async:%"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0465UrmaCmdFreeJfcFailure::GetName() const
{
    return "urma_cmd_free_jfc 确认事件失败";
}

std::string Urma0465UrmaCmdFreeJfcFailure::GetRootCauseDesc() const
{
    return "源码在该错误分支记录 URMA_LOG_ERR，通常表示当前函数检测到参数、状态、资源或下游返回值异常";
}

RootCause Urma0465UrmaCmdFreeJfcFailure::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0465UrmaCmdFreeJfcFailure::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0465UrmaCmdFreeJfcFailure::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：There is jfc event and it must be acked, jfc_comp:%, comp:%, "
           "jfc_async:%, async:%";
}

std::string Urma0465UrmaCmdFreeJfcFailure::GetId() const
{
    return "urma_0465";
}
} // namespace diag
