#include "urma_failure_540.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure540> g_urma("urma_540");

bool UrmaFailure540::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_unimport_seg' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'dev not support token id table mode.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure540::GetName() const
{
    return "解除导入设备过程中依赖步骤失败";
}

std::string UrmaFailure540::GetRootCauseDesc() const
{
    return "函数用于解除导入设备，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URM"
           "A操作失败。";
}

RootCause UrmaFailure540::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure540::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure540::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_unimport_seg，dev not support token id table mode.。";
}

std::string UrmaFailure540::GetId() const
{
    return "urma_540";
}

} // namespace diag
