#include "urma_failure_566.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure566> g_urma("urma_566");

bool UrmaFailure566::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'convert_jfs_vwr_to_pwr' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Unsupported send opcode'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure566::GetName() const
{
    return "JFS数据通路处理失败";
}

std::string UrmaFailure566::GetRootCauseDesc() const
{
    return "函数处理URMA数据收发路径，需要完成WR转换、投递、完成事件处理或重传，相关对象状态或下层操作失败导致数据通路"
           "中断。";
}

RootCause UrmaFailure566::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure566::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure566::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：convert_jfs_vwr_to_pwr，Unsupported send opcode。";
}

std::string UrmaFailure566::GetId() const
{
    return "urma_566";
}

} // namespace diag
