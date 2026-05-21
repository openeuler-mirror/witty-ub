#include "urma_failure_613.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure613> g_urma("urma_613");

bool UrmaFailure613::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && "
        "grep -F 'urma_unregister_seg' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F '[DRV_ERR]Unregister seg fail, dev_name:' | "
        "grep -F ', eid_idx:' | "
        "grep -F ', tid:' | "
        "grep -F ', ret:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure613::GetName() const
{
    return "urma_unregister_seg 执行注册 设备 失败导致当前资源状态无法推进";
}

std::string UrmaFailure613::GetRootCauseDesc() const
{
    return "urma_unregister_seg 调用下层 provider、bond 组件或系统接口处理 设备 时返回失败，当前分支携带 ret/errno "
           "等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。";
}

RootCause UrmaFailure613::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure613::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure613::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：[DRV_ERR]Unregister seg fail, dev_name: , eid_idx: , tid: , ret";
}

std::string UrmaFailure613::GetId() const
{
    return "urma_613";
}

} // namespace diag
