#include "urma_failure_703.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure703> g_urma("urma_703");

bool UrmaFailure703::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_cmd_set_jfc_opt' \"$URMA_LOG_PATH\" 2>/dev/null | grep -F 'ioctl "
        "failed in urma_cmd_set_jfc_opt, ret:' | grep -F ', errno:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure703::GetName() const
{
    return "设置ioctl的ioctl调用返回失败";
}

std::string UrmaFailure703::GetRootCauseDesc() const
{
    return "函数通过ioctl向URMA内核驱动提交设置ioctl请求，驱动返回错误或系统调用失败，用户态无法获得预期的驱动处理结果"
           "。";
}

RootCause UrmaFailure703::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure703::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure703::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_set_jfc_opt，ioctl failed in urma_cmd_set_jfc_opt, ret:，, "
           "errno:。";
}

std::string UrmaFailure703::GetId() const
{
    return "urma_703";
}

} // namespace diag
