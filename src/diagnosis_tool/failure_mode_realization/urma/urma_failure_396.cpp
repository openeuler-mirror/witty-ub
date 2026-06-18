#include "urma_failure_396.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure396> g_urma("urma_396");

bool UrmaFailure396::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bondp_flush_jetty") != std::string::npos &&
           message.find("Failed to flush pjetty[") != std::string::npos && message.find("]:") != std::string::npos;
}

std::string UrmaFailure396::GetName() const
{
    return "数据通路操作返回失败导致刷新Jetty失败";
}

std::string UrmaFailure396::GetRootCauseDesc() const
{
    return "bondp_flush_"
           "jetty执行数据收发相关操作时，下层队列、完成队列或provider返回错误，导致请求无法正常提交或回收。";
}

RootCause UrmaFailure396::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure396::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure396::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_flush_jetty，Failed to flush pjetty[，]:。";
}

std::string UrmaFailure396::GetId() const
{
    return "urma_396";
}
} // namespace diag
