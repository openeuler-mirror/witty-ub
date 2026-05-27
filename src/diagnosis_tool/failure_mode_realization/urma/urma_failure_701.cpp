#include "urma_failure_701.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure701> g_urma("urma_701");

bool UrmaFailure701::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_cmd_modify_jfr' \"$URMA_LOG_PATH\" 2>/dev/null | grep -F 'ioctl "
        "failed in urma_cmd_modify_jfr, ret:' | grep -F ', errno:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure701::GetName() const
{
    return "修改ioctl的ioctl调用返回失败";
}

std::string UrmaFailure701::GetRootCauseDesc() const
{
    return "函数通过ioctl向URMA内核驱动提交修改ioctl请求，驱动返回错误或系统调用失败，用户态无法获得预期的驱动处理结果"
           "。";
}

RootCause UrmaFailure701::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure701::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure701::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_modify_jfr，ioctl failed in urma_cmd_modify_jfr, ret:，, "
           "errno:。";
}

std::string UrmaFailure701::GetId() const
{
    return "urma_701";
}

} // namespace diag
