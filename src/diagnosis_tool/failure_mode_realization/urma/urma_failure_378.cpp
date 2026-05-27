#include "urma_failure_378.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure378> g_urma("urma_378");

bool UrmaFailure378::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_cmd_alloc_jfc' \"$URMA_LOG_PATH\" 2>/dev/null | grep -F 'ioctl "
        "failed in urma_cmd_alloc_jfc, ret:' | grep -F ', errno:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure378::GetName() const
{
    return "ioctl相关临时结构或命令参数分配失败";
}

std::string UrmaFailure378::GetRootCauseDesc() const
{
    return "函数在分配ioctl前需要申请命令参数、资源描述或临时缓存，内存分配失败会阻断后续URMA资源处理。";
}

RootCause UrmaFailure378::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure378::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure378::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_alloc_jfc，ioctl failed in urma_cmd_alloc_jfc, ret:，, "
           "errno:。";
}

std::string UrmaFailure378::GetId() const
{
    return "urma_378";
}

} // namespace diag
