#include "urma_1014_import_pseg_import_segment_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma1014ImportPsegImportSegmentFailure> g_urma("urma_1014");

bool Urma1014ImportPsegImportSegmentFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to import seg (%, %)"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma1014ImportPsegImportSegmentFailure::GetName() const
{
    return "import_pseg 导入Segment失败";
}

std::string Urma1014ImportPsegImportSegmentFailure::GetRootCauseDesc() const
{
    return "资源操作失败，可能由于对象状态不匹配、参数非法、设备能力不支持或下游 provider/driver 返回错误；该路径返回 "
           "BONDP_ERROR";
}

RootCause Urma1014ImportPsegImportSegmentFailure::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma1014ImportPsegImportSegmentFailure::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma1014ImportPsegImportSegmentFailure::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to import seg (%, %)";
}

std::string Urma1014ImportPsegImportSegmentFailure::GetId() const
{
    return "urma_1014";
}
} // namespace diag
