#include "urma_failure_432.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure432> g_urma("urma_432");

bool UrmaFailure432::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_cmd_get_jfc_opt' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'ioctl failed in urma_cmd_get_jfc_opt, ret:' | grep -F ', errno:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure432::GetName() const
{
    return "获取ioctl的ioctl调用返回失败";
}

std::string UrmaFailure432::GetRootCauseDesc() const
{
    return "函数通过ioctl向URMA内核驱动提交获取ioctl请求，驱动返回错误或系统调用失败，用户态无法获得预期的驱动处理结果"
           "。";
}

RootCause UrmaFailure432::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure432::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure432::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_cmd_get_jfc_opt，ioctl failed in urma_cmd_get_jfc_opt, ret:，, errno:";
}

std::string UrmaFailure432::GetId() const
{
    return "urma_432";
}

} // namespace diag
