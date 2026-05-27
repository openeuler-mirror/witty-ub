#include "urma_failure_375.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure375> g_urma("urma_375");

bool UrmaFailure375::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_cmd_alloc_jfc' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'ioctl failed in urma_cmd_alloc_jfc, ret:' | grep -F ', errno:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure375::GetName() const
{
    return "ioctl相关临时结构或命令参数分配失败";
}

std::string UrmaFailure375::GetRootCauseDesc() const
{
    return "函数在分配ioctl前需要申请命令参数、资源描述或临时缓存，内存分配失败会阻断后续URMA资源处理。";
}

RootCause UrmaFailure375::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure375::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure375::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_cmd_alloc_jfc，ioctl failed in urma_cmd_alloc_jfc, ret:，, errno:";
}

std::string UrmaFailure375::GetId() const
{
    return "urma_375";
}

} // namespace diag
