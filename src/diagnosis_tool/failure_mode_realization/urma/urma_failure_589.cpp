#include "urma_failure_589.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure589> g_urma("urma_589");

bool UrmaFailure589::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_delete_jetty") != std::string::npos &&
           message.find("jetty still deactived, can not delete.") != std::string::npos;
}

std::string UrmaFailure589::GetName() const
{
    return "Jetty状态不满足要求导致删除Jetty失败";
}

std::string UrmaFailure589::GetRootCauseDesc() const
{
    return "urma_delete_jetty执行删除Jetty时检测到依赖对象、资源状态或返回值异常，因此中止当前URMA操作。";
}

RootCause UrmaFailure589::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure589::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure589::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_delete_jetty，jetty still deactived, can not delete.。";
}

std::string UrmaFailure589::GetId() const
{
    return "urma_589";
}
} // namespace diag
