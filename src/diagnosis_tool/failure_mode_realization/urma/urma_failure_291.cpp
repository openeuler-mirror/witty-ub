#include "urma_failure_291.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure291> g_urma("urma_291");

bool UrmaFailure291::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && "
        "grep -F 'deepcopy_sg' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Failed to alloc dst sge'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure291::GetName() const
{
    return "deepcopy_sg 分配 SGE 临时参数失败导致复制流程无法继续";
}

std::string UrmaFailure291::GetRootCauseDesc() const
{
    return "deepcopy_sg 需要为 SGE 构造命令参数、资源描述或临时缓存，但内存分配返回失败，后续 provider "
           "调用或驱动命令缺少必要入参，因此当前 URMA 操作被阻断。";
}

RootCause UrmaFailure291::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure291::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure291::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Failed to alloc dst sge";
}

std::string UrmaFailure291::GetId() const
{
    return "urma_291";
}

} // namespace diag
