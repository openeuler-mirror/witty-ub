#include "urma_failure_372.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure372> g_urma("urma_372");

bool UrmaFailure372::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'urma_alloc_jfc' "$URMA_LOG_PATH" 2>/dev/null | grep -F 'failed to exec ops->alloc_jfc')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure372::GetName() const
{
    return "urma_alloc_jfc 分配 JFC 临时参数失败导致分配流程无法继续";
}

std::string UrmaFailure372::GetRootCauseDesc() const
{
    return "urma_alloc_jfc 需要为 JFC 构造命令参数、资源描述或临时缓存，但内存分配返回失败，后续 provider "
           "调用或驱动命令缺少必要入参，因此当前 URMA 操作被阻断。";
}

RootCause UrmaFailure372::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure372::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure372::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：failed to exec ops->alloc_jfc";
}

std::string UrmaFailure372::GetId() const
{
    return "urma_372";
}

} // namespace diag
