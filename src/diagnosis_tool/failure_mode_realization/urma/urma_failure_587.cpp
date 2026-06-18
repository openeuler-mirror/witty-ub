#include "urma_failure_587.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure587> g_urma("urma_587");

bool UrmaFailure587::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_free_jetty") != std::string::npos &&
           message.find("jetty still actived, please deactived first") != std::string::npos;
}

std::string UrmaFailure587::GetName() const
{
    return "Jetty状态不满足要求导致释放Jetty失败";
}

std::string UrmaFailure587::GetRootCauseDesc() const
{
    return "urma_free_jetty执行释放Jetty时检测到依赖对象、资源状态或返回值异常，因此中止当前URMA操作。";
}

RootCause UrmaFailure587::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure587::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure587::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_free_jetty，jetty still actived, please deactived first。";
}

std::string UrmaFailure587::GetId() const
{
    return "urma_587";
}
} // namespace diag
