#include "urma_failure_537.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure537> g_urma("urma_537");

bool UrmaFailure537::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_check_seg_cfg' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F '[DRV_ERR]register seg failed, dev_name:' | grep -F ', eid_idx:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure537::GetName() const
{
    return "Segment注册时下层资源准备失败";
}

std::string UrmaFailure537::GetRootCauseDesc() const
{
    return "函数负责注册Segment，依赖的provider接口、驱动命令、子资源或路由信息未成功返回，导致资源无法建立。";
}

RootCause UrmaFailure537::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure537::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure537::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_check_seg_cfg，[DRV_ERR]register seg failed, dev_name:，, eid_idx:";
}

std::string UrmaFailure537::GetId() const
{
    return "urma_537";
}

} // namespace diag
