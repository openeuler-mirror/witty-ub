#include "urma_failure_331.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure331> g_urma("urma_331");

bool UrmaFailure331::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && "
        "grep -F 'urma_cmd_alloc_jfc' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'ioctl failed in urma_cmd_alloc_jfc, ret:' | "
        "grep -F ', errno:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure331::GetName() const
{
    return "urma_cmd_alloc_jfc 分配 JFC 临时参数失败导致分配流程无法继续";
}

std::string UrmaFailure331::GetRootCauseDesc() const
{
    return "urma_cmd_alloc_jfc 需要为 JFC 构造命令参数、资源描述或临时缓存，但内存分配返回失败，后续 provider "
           "调用或驱动命令缺少必要入参，因此当前 URMA 操作被阻断。";
}

RootCause UrmaFailure331::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure331::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure331::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：ioctl failed in urma_cmd_alloc_jfc, ret:, errno";
}

std::string UrmaFailure331::GetId() const
{
    return "urma_331";
}

} // namespace diag
