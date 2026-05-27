#include "urma_failure_578.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure578> g_urma("urma_578");

bool UrmaFailure578::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_active_jfr' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'jfr or jfc state is wrong in active_jfr.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure578::GetName() const
{
    return "JFR数据通路处理失败";
}

std::string UrmaFailure578::GetRootCauseDesc() const
{
    return "函数处理URMA数据收发路径，需要完成WR转换、投递、完成事件处理或重传，相关对象状态或下层操作失败导致数据通路"
           "中断。";
}

RootCause UrmaFailure578::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure578::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure578::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_active_jfr，jfr or jfc state is wrong in active_jfr.。";
}

std::string UrmaFailure578::GetId() const
{
    return "urma_578";
}

} // namespace diag
