#include "urma_failure_178.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure178> g_urma("urma_178");

bool UrmaFailure178::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_cmd_get_tp_attr' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Failed in ioctl get_tp_attr, ret:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure178::GetName() const
{
    return "获取ioctl的ioctl调用返回失败";
}

std::string UrmaFailure178::GetRootCauseDesc() const
{
    return "函数通过ioctl向URMA内核驱动提交获取ioctl请求，驱动返回错误或系统调用失败，用户态无法获得预期的驱动处理结果"
           "。";
}

RootCause UrmaFailure178::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure178::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure178::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_get_tp_attr，Failed in ioctl get_tp_attr, ret:。";
}

std::string UrmaFailure178::GetId() const
{
    return "urma_178";
}

} // namespace diag
