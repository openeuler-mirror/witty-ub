#include "urma_failure_542.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure542> g_urma("urma_542");

bool UrmaFailure542::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_check_seg_cfg' \"$URMA_LOG_PATH\" 2>/dev/null | grep -F "
        "'[DRV_ERR]register seg failed, dev_name:' | grep -F ', eid_idx:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure542::GetName() const
{
    return "Segment注册时下层资源准备失败";
}

std::string UrmaFailure542::GetRootCauseDesc() const
{
    return "函数负责注册Segment，依赖的provider接口、驱动命令、子资源或路由信息未成功返回，导致资源无法建立。";
}

RootCause UrmaFailure542::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure542::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure542::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_check_seg_cfg，[DRV_ERR]register seg failed, dev_name:，, "
           "eid_idx:。";
}

std::string UrmaFailure542::GetId() const
{
    return "urma_542";
}

} // namespace diag
