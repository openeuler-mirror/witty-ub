#include "urma_failure_532.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure532> g_urma("urma_532");

bool UrmaFailure532::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_unimport_seg' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F '[DRV_ERR]Failed to register seg, dev_name:' | grep -F ', eid_idx:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure532::GetName() const
{
    return "Segment注册时下层资源准备失败";
}

std::string UrmaFailure532::GetRootCauseDesc() const
{
    return "函数负责注册Segment，依赖的provider接口、驱动命令、子资源或路由信息未成功返回，导致资源无法建立。";
}

RootCause UrmaFailure532::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure532::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure532::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_unimport_seg，[DRV_ERR]Failed to register seg, dev_name:，, eid_idx:";
}

std::string UrmaFailure532::GetId() const
{
    return "urma_532";
}

} // namespace diag
