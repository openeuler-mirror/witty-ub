#include "urma_failure_151.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure151> g_urma("urma_151");

bool UrmaFailure151::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bondp_create_jetty") != std::string::npos &&
           message.find("Failed to add jetty id to p_vjetty_id table") != std::string::npos;
}

std::string UrmaFailure151::GetName() const
{
    return "创建Jetty执行失败导致创建Jetty失败";
}

std::string UrmaFailure151::GetRootCauseDesc() const
{
    return "bondp_create_jetty创建Jetty时初始化端口索引或收发WR缓冲区失败，当前URMA操作无法继续完成。";
}

RootCause UrmaFailure151::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure151::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure151::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_create_jetty，Failed to add jetty id to p_vjetty_id table。";
}

std::string UrmaFailure151::GetId() const
{
    return "urma_151";
}
} // namespace diag
