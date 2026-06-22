#include "urma_failure_299.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure299> g_urma("urma_299");

bool UrmaFailure299::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bondp_register_health_check_seg_for_jetty") != std::string::npos &&
           message.find("Failed to alloc health check buffer") != std::string::npos;
}

std::string UrmaFailure299::GetName() const
{
    return "health、Segment、FOR临时结构分配失败导致注册health、Segment、FOR失败";
}

std::string UrmaFailure299::GetRootCauseDesc() const
{
    return "bondp_register_health_check_seg_for_"
           "jetty执行注册health、Segment、FOR前需要准备health、Segment、FOR临时结构，内存或资源分配失败会阻"
           "断后续URMA操作。";
}

RootCause UrmaFailure299::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure299::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure299::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_register_health_check_seg_for_jetty，Failed to alloc health check "
           "buffer"
           "。";
}

std::string UrmaFailure299::GetId() const
{
    return "urma_299";
}
} // namespace diag
