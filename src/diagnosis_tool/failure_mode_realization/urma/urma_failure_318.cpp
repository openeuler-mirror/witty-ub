#include "urma_failure_318.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure318> g_urma("urma_318");

bool UrmaFailure318::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && "
        "grep -F 'urma_cmd_alloc_jfs' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'ioctl failed in urma_cmd_alloc_jfr, ret:' | "
        "grep -F ', errno:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure318::GetName() const
{
    return "urma_cmd_alloc_jfs 分配 JFS 临时参数失败导致分配流程无法继续";
}

std::string UrmaFailure318::GetRootCauseDesc() const
{
    return "urma_cmd_alloc_jfs 需要为 JFS 构造命令参数、资源描述或临时缓存，但内存分配返回失败，后续 provider "
           "调用或驱动命令缺少必要入参，因此当前 URMA 操作被阻断。";
}

RootCause UrmaFailure318::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure318::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure318::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：ioctl failed in urma_cmd_alloc_jfr, ret:, errno";
}

std::string UrmaFailure318::GetId() const
{
    return "urma_318";
}

} // namespace diag
