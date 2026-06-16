#include "urma_failure_545.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure545> g_urma("urma_545");

bool UrmaFailure545::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_unregister_seg' \"$URMA_LOG_PATH\" 2>/dev/null | grep -F "
        "'[DRV_ERR]Unregister seg fail, dev_name:' | grep -F ', eid_idx:' | grep -F ', tid:' | grep -F ', ret:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure545::GetName() const
{
    return "Segment清理阶段下层释放操作失败";
}

std::string UrmaFailure545::GetRootCauseDesc() const
{
    return "函数负责释放或撤销Segment相关资源，下层provider、驱动或引用状态返回失败，可能残留已创建的URMA资源。";
}

RootCause UrmaFailure545::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure545::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure545::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_unregister_seg，[DRV_ERR]Unregister seg fail, dev_name:，, "
           "eid_idx:，, tid:，, ret:。";
}

std::string UrmaFailure545::GetId() const
{
    return "urma_545";
}

} // namespace diag
