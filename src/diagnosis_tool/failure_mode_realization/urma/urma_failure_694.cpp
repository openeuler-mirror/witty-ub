#include "urma_failure_694.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure694> g_urma("urma_694");

bool UrmaFailure694::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_cmd_modify_jfc' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'ioctl failed in urma_cmd_modify_jfc, ret:' | grep -F ', errno:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure694::GetName() const
{
    return "修改ioctl的ioctl调用返回失败";
}

std::string UrmaFailure694::GetRootCauseDesc() const
{
    return "函数通过ioctl向URMA内核驱动提交修改ioctl请求，驱动返回错误或系统调用失败，用户态无法获得预期的驱动处理结果"
           "。";
}

RootCause UrmaFailure694::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure694::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure694::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_cmd_modify_jfc，ioctl failed in urma_cmd_modify_jfc, ret:，, errno:";
}

std::string UrmaFailure694::GetId() const
{
    return "urma_694";
}

} // namespace diag
