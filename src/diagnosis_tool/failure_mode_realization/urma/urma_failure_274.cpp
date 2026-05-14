#include "urma_failure_274.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure274> g_urma("urma_274");

bool UrmaFailure274::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'bondp_register_seg' "$URMA_LOG_PATH" 2>/dev/null | grep -F 'Failed to alloc bondp segment comp')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure274::GetName() const
{
    return "bondp_register_seg 分配 segment 临时参数失败导致注册流程无法继续";
}

std::string UrmaFailure274::GetRootCauseDesc() const
{
    return "bondp_register_seg 需要为 segment 构造命令参数、资源描述或临时缓存，但内存分配返回失败，后续 provider "
           "调用或驱动命令缺少必要入参，因此当前 URMA 操作被阻断。";
}

RootCause UrmaFailure274::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure274::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure274::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Failed to alloc bondp segment comp";
}

std::string UrmaFailure274::GetId() const
{
    return "urma_274";
}

} // namespace diag
