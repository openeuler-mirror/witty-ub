#include "urma_failure_392.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure392> g_urma("urma_392");

bool UrmaFailure392::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_check_order_type' \"$URMA_LOG_PATH\" 2>/dev/null | grep -F "
        "'[DRV_ERR]Failed to create jfs, dev_name:' | grep -F ', eid_idx:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure392::GetName() const
{
    return "JFS创建时下层资源准备失败";
}

std::string UrmaFailure392::GetRootCauseDesc() const
{
    return "函数负责创建JFS，依赖的provider接口、驱动命令、子资源或路由信息未成功返回，导致资源无法建立。";
}

RootCause UrmaFailure392::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure392::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure392::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_check_order_type，[DRV_ERR]Failed to create jfs, dev_name:，, "
           "eid_idx:。";
}

std::string UrmaFailure392::GetId() const
{
    return "urma_392";
}

} // namespace diag
