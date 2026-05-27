#include "urma_failure_557.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure557> g_urma("urma_557");

bool UrmaFailure557::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'post_recv_check_wr_list_valid' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid bdp_recv_comp type:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure557::GetName() const
{
    return "设备对象、sysfs设备信息、WR对象无效导致投递组件失败";
}

std::string UrmaFailure557::GetRootCauseDesc() const
{
    return "函数用于投递组件，调用方传入的设备对象、sysfs设备信息、WR对象不满足接口前置条件，无法继续完成本次URMA操作"
           "。";
}

RootCause UrmaFailure557::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure557::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure557::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：post_recv_check_wr_list_valid，Invalid bdp_recv_comp type:";
}

std::string UrmaFailure557::GetId() const
{
    return "urma_557";
}

} // namespace diag
