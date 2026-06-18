#include "urma_failure_013.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure013> g_urma("urma_013");

bool UrmaFailure013::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bondp_import_jetty") != std::string::npos &&
           message.find("Failed to init active indices") != std::string::npos;
}

std::string UrmaFailure013::GetName() const
{
    return "导入Jetty执行失败导致导入Jetty失败";
}

std::string UrmaFailure013::GetRootCauseDesc() const
{
    return "bondp_import_jetty导入Jetty时初始化端口索引或目标端端口索引失败，当前URMA操作无法继续完成。";
}

RootCause UrmaFailure013::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure013::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure013::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_import_jetty，Failed to init active indices。";
}

std::string UrmaFailure013::GetId() const
{
    return "urma_013";
}
} // namespace diag
